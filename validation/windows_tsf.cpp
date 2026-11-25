// Acts as a TSF client on the editor window thread. All text and geometry go
// through the OS context.
#define WIN32_LEAN_AND_MEAN
#include <msctf.h>
#include <new>
#include <string>
#include <windows.h>
#include <wrl/client.h>

using Microsoft::WRL::ComPtr;

namespace {
ComPtr<ITfThreadMgr> manager;
ComPtr<ITfContext> context;
ComPtr<ITfComposition> composition;
TfClientId client = TF_CLIENTID_NULL;
int detail = 0;

class CompositionSink final : public ITfCompositionSink {
  LONG refs_ = 1;

public:
  HRESULT STDMETHODCALLTYPE QueryInterface(REFIID id, void **out) override {
    if (!out)
      return E_POINTER;
    *out = nullptr;
    if (id != IID_IUnknown && id != IID_ITfCompositionSink)
      return E_NOINTERFACE;
    *out = static_cast<ITfCompositionSink *>(this);
    AddRef();
    return S_OK;
  }
  ULONG STDMETHODCALLTYPE AddRef() override {
    return InterlockedIncrement(&refs_);
  }
  ULONG STDMETHODCALLTYPE Release() override {
    ULONG remaining = InterlockedDecrement(&refs_);
    if (!remaining)
      delete this;
    return remaining;
  }
  HRESULT STDMETHODCALLTYPE OnCompositionTerminated(TfEditCookie,
                                                    ITfComposition *) override {
    return S_OK;
  }
};

class Session final : public ITfEditSession {
  LONG refs_ = 1;
  int step_;

public:
  explicit Session(int step) : step_(step) {}
  HRESULT STDMETHODCALLTYPE QueryInterface(REFIID id, void **out) override {
    if (!out)
      return E_POINTER;
    *out = nullptr;
    if (id != IID_IUnknown && id != IID_ITfEditSession)
      return E_NOINTERFACE;
    *out = static_cast<ITfEditSession *>(this);
    AddRef();
    return S_OK;
  }
  ULONG STDMETHODCALLTYPE AddRef() override {
    return InterlockedIncrement(&refs_);
  }
  ULONG STDMETHODCALLTYPE Release() override {
    ULONG remaining = InterlockedDecrement(&refs_);
    if (!remaining)
      delete this;
    return remaining;
  }
  HRESULT STDMETHODCALLTYPE DoEditSession(TfEditCookie cookie) override {
    if (step_ == 2) {
      ComPtr<ITfRange> range;
      detail = 20;
      HRESULT hr = composition->GetRange(&range);
      if (FAILED(hr))
        return hr;
      detail = 21;
      hr = range->SetText(cookie, 0, L"\u4e2d", 1);
      if (FAILED(hr))
        return hr;
      detail = 22;
      return composition->EndComposition(cookie);
    }
    ComPtr<ITfRange> start, end;
    detail = 5;
    HRESULT hr = context->GetStart(cookie, &start);
    if (SUCCEEDED(hr))
      hr = context->GetEnd(cookie, &end);
    if (SUCCEEDED(hr))
      hr = start->ShiftEndToRange(cookie, end.Get(), TF_ANCHOR_END);
    if (FAILED(hr))
      return hr;
    WCHAR buffer[24] = {};
    ULONG count = 0;
    detail = 6;
    hr = start->GetText(cookie, 0, buffer, ARRAYSIZE(buffer), &count);
    if (FAILED(hr) || std::wstring(buffer, count) != L"A\U0001f642B")
      return E_FAIL;
    TF_SELECTION selection{};
    ULONG found = 0;
    detail = 7;
    hr = context->GetSelection(cookie, TF_DEFAULT_SELECTION, 1, &selection,
                               &found);
    if (FAILED(hr) || found != 1)
      return E_FAIL;
    ComPtr<ITfRange> caret;
    caret.Attach(selection.range);
    ComPtr<ITfContextView> view;
    RECT rect{};
    BOOL clipped = FALSE;
    detail = 8;
    hr = context->GetActiveView(&view);
    if (SUCCEEDED(hr))
      hr = view->GetTextExt(cookie, caret.Get(), &rect, &clipped);
    if (FAILED(hr) || rect.bottom <= rect.top)
      return E_FAIL;
    ComPtr<ITfContextComposition> editor;
    detail = 9;
    hr = context.As(&editor);
    if (FAILED(hr))
      return hr;
    ComPtr<ITfCompositionSink> sink;
    sink.Attach(new (std::nothrow) CompositionSink());
    if (!sink)
      return E_OUTOFMEMORY;
    detail = 10;
    hr =
        editor->StartComposition(cookie, caret.Get(), sink.Get(), &composition);
    if (FAILED(hr) || !composition)
      return E_FAIL;
    ComPtr<ITfRange> marked;
    detail = 11;
    hr = composition->GetRange(&marked);
    if (FAILED(hr))
      return hr;
    return marked->SetText(cookie, 0, L"zhong", 5);
  }
};

int nativeStep(HWND hwnd, int step) {
  if (step == 1) {
    ComPtr<ITfDocumentMgr> document;
    if (GetFocus() != hwnd)
      return 1;
    if (FAILED(CoCreateInstance(CLSID_TF_ThreadMgr, nullptr,
                                CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&manager))))
      return 2;
    if (FAILED(manager->Activate(&client)))
      return 3;
    if (FAILED(manager->GetFocus(&document)) || !document ||
        FAILED(document->GetTop(&context)) || !context)
      return 4;
  }
  if (!context || (step == 2 && !composition))
    return 23;
  ComPtr<ITfEditSession> session;
  session.Attach(new (std::nothrow) Session(step));
  if (!session)
    return 24;
  HRESULT outcome = E_FAIL;
  detail = 25;
  HRESULT hr = context->RequestEditSession(
      client, session.Get(), TF_ES_SYNC | TF_ES_READWRITE, &outcome);
  int error = SUCCEEDED(hr) && SUCCEEDED(outcome) ? 0 : detail;
  if (error || step == 2) {
    composition.Reset();
    context.Reset();
    manager->Deactivate();
    manager.Reset();
  }
  return error;
}
} // namespace
extern "C"
    __declspec(dllexport) int (*editor_tsf_probe)(HWND, int) = nativeStep;
